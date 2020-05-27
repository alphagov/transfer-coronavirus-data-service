import os
import sys

from config import setup_local_environment, setup_talisman, load_environment
from main import app


def run():
    """
    Run a local server
    """
    setup_talisman(app)
    load_environment(app)
    app.run(host="0.0.0.0", port=os.getenv("PORT", "8000"))


if __name__ == "__main__":

    if len(sys.argv) == 3:
        is_admin = sys.argv[1] == "admin"
        env_load = sys.argv[2]
    else:
        is_admin = False
        env_load = "testing"

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
        if env_load != "testing":
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

    setup_local_environment(is_admin=is_admin, environment=env_load)
    run()
