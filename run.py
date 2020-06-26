import os

import config
from main import app


def run():
    """
    Run a local server
    """
    config.load_environment(app)
    settings_loaded = config.load_settings(app)
    if settings_loaded:
        app.run(host="0.0.0.0", port=os.getenv("PORT", "8000"))
    else:
        green_char = "\033[92m"
        end_charac = "\033[0m"
        print("-" * 35)
        print("Please run: {}eval $(gds aws XXXX -e){}".format(green_char, end_charac))
        print("Where {}XXXX{} is the account to access".format(green_char, end_charac))
        print("Then run make again")
        print("-" * 35)
        exit()


if __name__ == "__main__":
    config.setup_local_environment(is_admin=True, environment="testing")
    run()
