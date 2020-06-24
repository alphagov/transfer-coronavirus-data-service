import os
import sys

import config
from main import app


def run():
    """
    Run a local server
    """
    config.load_environment(app)
    config.setup_talisman(app)
    ssm_loaded = config.load_ssm_parameters(app)
    if ssm_loaded:
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


def handle_args(is_admin, env_load):

    green_char = "\033[92m"
    end_charac = "\033[0m"

    print("-" * 35)
    print(
        "Running {0}{2}{1} for: {0}{3}{1}".format(
            green_char,
            end_charac,
            "admin tool" if is_admin else "download tool frontend",
            env_load,
        )
    )

    if sys.argv[0] == "run.py":
        cont = "y"
        if env_load not in ("testing", "dev-four"):
            try:
                cont = input(
                    "Not {}testing{}; do you want to continue? (Y/n) ".format(
                        green_char, end_charac
                    )
                ).lower()
                if cont == "":
                    cont = "y"
            except KeyboardInterrupt:
                print("\nRegistration cancelled.")
                exit()
        if cont != "y":
            exit()
    print("-" * 35)


if __name__ == "__main__":

    if len(sys.argv) == 3:
        is_admin = sys.argv[1] == "admin"
        env_load = sys.argv[2]
    else:
        is_admin = False
        env_load = "testing"

    handle_args(is_admin, env_load)
    config.setup_local_environment(is_admin=is_admin, environment=env_load)
    run()
