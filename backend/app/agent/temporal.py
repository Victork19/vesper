from datetime import datetime, timezone
from ..memory.models import Scar, HotState
def parse(s):
    try:return datetime.fromisoformat(s.replace('Z','+00:00'))
    except:return datetime.min.replace(tzinfo=timezone.utc)
def active_scars(scars, now=None):
    now=now or datetime.now(timezone.utc); return [s for s in scars if not s.cooldown_until or parse(s.cooldown_until)<=now]
def in_cooldown(scars, now=None):
    now=now or datetime.now(timezone.utc); return [s for s in scars if s.cooldown_until and parse(s.cooldown_until)>now]
