import json


def get_plot_link_handler(plot_id):
    test_links = {
        "Междуморье": "https://xn----7sbbqebqelognciq2b4r.xn--p1ai/midsea",
        "Победный берег": "https://xn----7sbbqebqelognciq2b4r.xn--p1ai/pobednyi",
        "Королёвские дачи": "https://xn----7sbbqebqelognciq2b4r.xn--p1ai/korolevo",
        "Усадьба Джарылгач": "https://xn----7sbbqebqelognciq2b4r.xn--p1ai/dzharylgach",
        "Великие Луга": "https://xn----7sbbqebqelognciq2b4r.xn--p1ai/velikieluga"
    }
    return test_links.get(plot_id, "Неизвестный участок")


def make_summary():
    pass

