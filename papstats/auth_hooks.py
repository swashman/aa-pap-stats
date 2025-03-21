# Alliance Auth
from allianceauth import hooks
from allianceauth.services.hooks import MenuItemHook, UrlHook

# Pap Stats
from papstats import __title__, urls


class ExampleMenuItem(MenuItemHook):
    """This class ensures only authorized users will see the menu entry"""

    def __init__(self):
        # setup menu entry for sidebar
        MenuItemHook.__init__(
            self,
            __title__,
            "fas fa-cube fa-fw",
            "papstats:index",
            navactive=["papstats:"],
        )

    def render(self, request):
        if request.user.has_perm("papstats.basic_access"):
            return MenuItemHook.render(self, request)
        return ""


@hooks.register("menu_item_hook")
def register_menu():
    return ExampleMenuItem()


@hooks.register("url_hook")
def register_urls():
    return UrlHook(urls, "papstats", r"^papstats/")
