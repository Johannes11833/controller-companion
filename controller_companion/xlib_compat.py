"""Runtime fix for Xauthority matching in the old python3-xlib 0.15.

pyautogui's X11 backend depends on the abandoned python3-xlib 0.15. Its
Xauthority lookup requires a cookie entry whose display number matches exactly,
but mutter writes the Xwayland cookie with an empty display number on
GNOME/Wayland sessions, so the lookup finds nothing and the X server rejects
the connection with "Authorization required". Newer python-xlib treats an empty
display number as a wildcard and connects fine; this patch applies the same
fallback on top of the original lookup.
"""


def patch_xlib_auth() -> None:
    """Accept Xauthority entries with an empty display number."""
    try:
        from Xlib import error, xauth
    except ImportError:
        return

    original = xauth.Xauthority.get_best_auth

    def get_best_auth(self, family, address, dispno, types=(b"MIT-MAGIC-COOKIE-1",)):
        try:
            return original(self, family, address, dispno, types)
        except error.XNoAuthError:
            pass

        num = str(dispno).encode()
        address = address.encode()
        matches = {}
        for efam, eaddr, enum, ename, edata in self.entries:
            if enum == b"" and ename not in matches:
                enum = num
            if efam == family and eaddr == address and num == enum:
                matches[ename] = edata
        for t in types:
            if t in matches:
                return (t, matches[t])
        raise error.XNoAuthError((family, address, dispno))

    xauth.Xauthority.get_best_auth = get_best_auth
