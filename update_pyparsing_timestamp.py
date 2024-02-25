from datetime import datetime
from pathlib import Path
from pyparsing import quoted_string

nw = datetime.utcnow()
now_string = f'"{nw.strftime("%d %b %Y %X")[:-3]} UTC"'
print(now_string)

quoted_time = quoted_string()
quoted_time.set_parse_action(lambda: now_string)

version_time = "__version_time__ = " + quoted_time

pp_init = Path("pyparsing/__init__.py")
orig_code = pp_init.read_text()
new_code = version_time.transform_string(orig_code)
pp_init.write_text(new_code)
