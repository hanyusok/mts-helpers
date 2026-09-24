from typing import Optional

def mask_korean_name(name: Optional[str]) -> str:
    """Masks a Korean name for privacy compliance (e.g. 홍길동 -> 홍*동, 김철 -> 김*, 남궁민수 -> 남**수)."""
    if not name:
        return ""
    s = str(name).strip()
    length = len(s)
    if length <= 1:
        return s
    elif length == 2:
        return s[0] + "*"
    else:
        return s[0] + "*" * (length - 2) + s[-1]
