from rad import Radario

r = Radario()
category = ["concert", "education", "theatre"]
from datetime import datetime as dt

date_from_dt = dt.now()
date_to_dt = dt.now()
e = r.get_events(category, date_from_dt, date_to_dt)
print(len(e))
print(e)
