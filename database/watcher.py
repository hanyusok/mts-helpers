import asyncio
import datetime
import logging
from database.firebird import get_db_connection, get_active_table, check_remote_server_alive
from routers.websockets import customer_notifier

logger = logging.getLogger("emr_watcher")

_table_cache = {}

def get_active_table_cached(db_name: str, prefix: str) -> str:
    today = datetime.date.today()
    cache_key = (db_name, prefix, today)
    if cache_key in _table_cache:
        return _table_cache[cache_key]
        
    table_name = get_active_table(db_name, prefix)
    _table_cache[cache_key] = table_name
    
    # Clean up old keys
    keys_to_del = [k for k in _table_cache if k[2] != today]
    for k in keys_to_del:
        del _table_cache[k]
        
    return table_name

def get_db_state():
    """Queries current today's state for both MTSMTR and MTSWAIT."""
    if not check_remote_server_alive(timeout=1.0):
        return None

    today = datetime.date.today()
    state = {}
    
    # 1. MTSMTR: track sequence ID, patient code, and completion status
    try:
        table_mtr = get_active_table_cached("MTSMTR", "MTR")
        wrapped_con = get_db_connection("MTSMTR")
        con = wrapped_con._connection
        cur = con.cursor()
        try:
            cur.execute(f'SELECT "#", PCODE, FIN FROM {table_mtr} WHERE VISIDATE = ? ORDER BY "#"', (today,))
            rows = cur.fetchall()
            state["MTSMTR"] = tuple(rows)
        finally:
            con.close()
    except Exception as e:
        logger.debug(f"Failed to query MTSMTR state: {e}")
        state["MTSMTR"] = ()

    # 2. MTSWAIT: track patient code and waitlist queue ID
    try:
        table_wait = get_active_table_cached("MTSWAIT", "WAIT")
        wrapped_con = get_db_connection("MTSWAIT")
        con = wrapped_con._connection
        cur = con.cursor()
        try:
            cur.execute(f"SELECT PCODE, RESID1 FROM {table_wait} WHERE VISIDATE = ? ORDER BY RESID1", (today,))
            rows = cur.fetchall()
            state["MTSWAIT"] = tuple(rows)
        finally:
            con.close()
    except Exception as e:
        logger.debug(f"Failed to query MTSWAIT state: {e}")
        state["MTSWAIT"] = ()
        
    return state

async def watch_db_changes():
    """Periodically queries Firebird to detect changes and broadcasts via WebSockets."""
    logger.info("Database change watcher loop started.")
    last_state = None
    
    while True:
        try:
            loop = asyncio.get_running_loop()
            current_state = await loop.run_in_executor(None, get_db_state)
            
            if current_state is not None:
                if last_state is not None and current_state != last_state:
                    logger.info("Detected Firebird waitlist/ledger change. Broadcasting QUEUE_UPDATE...")
                    await customer_notifier.broadcast({
                        "type": "QUEUE_UPDATE",
                        "timestamp": datetime.datetime.now().isoformat()
                    })
                last_state = current_state
        except asyncio.CancelledError:
            logger.info("Database change watcher task cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in database watcher: {e}")
            
        await asyncio.sleep(1.5)
