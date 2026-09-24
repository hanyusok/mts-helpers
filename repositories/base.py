import logging
from contextlib import contextmanager
from typing import Any, List, Optional, Tuple, Union

from database.firebird import get_db_connection, serialize_row

logger = logging.getLogger("emr_repo")

@contextmanager
def transaction_context(db_name: str, con=None):
    """
    Unit of Work Context Manager:
    Manages Firebird database connection and transaction lifecycle.
    If an existing connection `con` is passed, it reuses it without closing.
    If not, it opens a new connection, commits on success, rolls back on error, and closes cleanly.
    """
    close_con = False
    if con is None:
        con = get_db_connection(db_name)
        close_con = True
        
    try:
        yield con
        if close_con:
            con.commit()
    except Exception as e:
        if close_con and hasattr(con, "rollback"):
            try:
                con.rollback()
            except Exception as rb_ex:
                logger.error(f"[{db_name}] Rollback failed: {rb_ex}")
        raise e
    finally:
        if close_con:
            try:
                con.close()
            except Exception as cl_ex:
                logger.error(f"[{db_name}] Connection close failed: {cl_ex}")

def execute_query(
    db_name: str, 
    query: str, 
    params: Optional[Union[Tuple[Any, ...], List[Any]]] = None, 
    fetch: str = "all", 
    con=None
):
    """
    Executes a SQL query with managed transaction lifecycle.
    `fetch` options: 'all', 'one', 'none'
    """
    with transaction_context(db_name, con=con) as active_con:
        cur = active_con.cursor()
        cur.execute(query, tuple(params) if params else None)
        
        if fetch == "one":
            row = cur.fetchone()
            if not row:
                return None
            cols = [desc[0] for desc in cur.description]
            return serialize_row(cols, row)
        elif fetch == "all":
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description]
            return [serialize_row(cols, r) for r in rows]
        else:
            return None
