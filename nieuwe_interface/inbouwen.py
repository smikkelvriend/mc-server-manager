"""Bouwt de nieuwe interface uit desk_bron.html (+ onderdelen van de telefoonpagina) en zet het in mc_server_manager.py."""
import os, re, sys
here = os.path.dirname(os.path.abspath(__file__))
py = os.path.join(here, "..", "mc_server_manager.py")
s = open(py, encoding="utf-8").read()
a = s.index('REMOTE_PAGE = r"""') + len('REMOTE_PAGE = r"""')
phone = s[a:s.index('"""', a)]
p1 = phone[phone.index("/* ---------- Plugins ---------- */"):phone.index("/* ---------- Beheer ---------- */")]
p1 = p1.replace("$('main')", "$('view')")
p2 = phone[phone.index("async function behB()"):phone.index("/* ---------- Meer ---------- */")]
p2 = re.sub(r"const dur=.*?\n", "", p2, count=1)
p2 = re.sub(r"async function behP\(\).*?\n(?=async function behT)", "", p2, count=1, flags=re.S)
assert "behP" not in p2.split("async function behT")[0], "behP niet verwijderd"
src = open(os.path.join(here, "desk_bron.html"), encoding="utf-8").read()
src = src.replace("//@@KOPIE_PLUGINS_KAART@@", p1).replace("//@@KOPIE_BEHEER@@", p2)
assert '"""' not in src and not src.rstrip().endswith("\\")
pass
m0, m1 = s.index("# <<DESK_PAGE\n"), s.index("# DESK_PAGE>>")
s = s[:m0] + '# <<DESK_PAGE\nDESK_PAGE = r"""' + src + '"""\n' + s[m1:]
open(py, "w", encoding="utf-8").write(s)
print("ingebouwd,", len(src), "tekens")
