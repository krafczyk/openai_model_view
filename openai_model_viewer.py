import curses
import openai
import json
import argparse
from enum import Enum

### Openai Methods
def list_available_models():
    models = openai.Model.list()
    return models

### Curses Methods
class ViewerMode(Enum):
    main_menu = 1
    list_models = 2
    view_model = 3

class ViewerState:
    enter_key = 10

    def __init__(self, log=None):
        self.mode = ViewerMode.main_menu
        self.models = None
        self.current_choice = 0
        self.save_choice = None
        self.menu_items = []
        self.goto_main_menu()
        if log is not None:
            self.log = open(log, 'w')
        else:
            self.log = None

    def print_to_log(self, *args, **kwargs):
        if self.log is not None:
            print(*args, file=self.log, **kwargs)

    def goto_main_menu(self):
        self.mode = ViewerMode.main_menu
        self.menu_items = [ "List Available Models", "Quit" ]

    def goto_list_models(self, reset_choice=True):
        self.mode = ViewerMode.list_models
        if reset_choice:
            self.current_choice = 0
        else:
            if self.save_choice is not None:
                self.current_choice = self.save_choice
                self.save_choice = None
        self.menu_items = [ f"{model.id}, created at: {ViewerState.format_unix_timestamp(model.__dict__['_previous']['created'])}" for model in self.models.data ]
        self.menu_items.append("Back")

    @staticmethod
    def format_unix_timestamp(timestamp):
        import datetime
        return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

    def goto_view_model(self):
        self.mode = ViewerMode.view_model
        self.save_choice = self.current_choice
        self.current_choice = -1
        # get model details
        model = self.models.data[self.save_choice]
        model_data = model._previous
        self.menu_items = [
            f"ID: {model_data['id']}",
            f"Created: {ViewerState.format_unix_timestamp(model_data['created'])}",
            #f"Owner: {model.owner}",
            #f"Organization: {model.organization}",
        ]

    def handle_key(self, stdscr, key):
        self.print_to_log(f"handle_key got key: {key} ({curses.keyname(key)})")

        # First, handle keyboard arrows
        if key == curses.KEY_UP:
            self.current_choice -= 1
            if self.current_choice < 0:
                self.current_choice = 0
            self.print_to_log("Handled key up")
            self.print_to_log("Current choice: ", self.current_choice)
        elif key == curses.KEY_DOWN:
            self.current_choice += 1
            if self.current_choice > len(self.menu_items) - 1:
                self.current_choice = len(self.menu_items) - 1
            self.print_to_log("Handled key down")
            self.print_to_log("Current choice: ", self.current_choice)
        # Handle quit keys
        if key == ord('q') or key == ord('Q'):
            self.print_to_log("Handled quit key")
            return False
        if key == 27:
            self.print_to_log("Handled quit key")
            # Don't wait for another key
            # If it was Alt then curses has already sent the other key
            # otherwise -1 is sent (Escape)
            stdscr.nodelay(True)
            n = stdscr.getch()
            if n == -1:
                # Escape was pressed
                # Return to delay
                stdscr.nodelay(False)
                return False
        # Handle other keys depending on mode
        if self.mode == ViewerMode.main_menu:
            self.print_to_log(f"In main_menu state")
            # curses number key or enter key, or keyboard key
            if key == 1 or ((key == ViewerState.enter_key or key == curses.KEY_RIGHT) and self.current_choice == 0):
                self.models = openai.Model.list()
                self.print_to_log(f"models type: {type(self.models)}")
                self.goto_list_models()
            elif key == 2 or ((key == ViewerState.enter_key or key == curses.KEY_RIGHT) and self.current_choice == 1):
                return False
        elif self.mode == ViewerMode.list_models:
            self.print_to_log(f"In list_models state")
            if key == ViewerState.enter_key or key == curses.KEY_RIGHT:
                if self.current_choice == len(self.menu_items) - 1 and self.menu_items[self.current_choice] == "Back":
                    # Back
                    self.goto_main_menu()
                    return True
                # Display model details
                self.goto_view_model()
                self.mode = ViewerMode.view_model
            elif key == curses.KEY_BACKSPACE or key == curses.KEY_LEFT:
                self.goto_main_menu()
        elif self.mode == ViewerMode.view_model:
            self.print_to_log(f"In view_model state")
            if key == curses.KEY_BACKSPACE or key == curses.KEY_LEFT:
                self.goto_list_models(reset_choice=False)
        else:
            raise ValueError("Invalid state")
            

        return True

    def display(self, stdscr):
        stdscr.clear()
        stdscr.addstr(1, 1, "OpenAI Model Viewer", curses.A_BOLD | curses.color_pair(1))

        for i, element in enumerate(self.menu_items):
            highlight = curses.A_REVERSE if i == self.current_choice else curses.A_NORMAL
            stdscr.addstr(3 + i, 3, f"{i + 1}. {element}", highlight)

        stdscr.refresh()

        choice = stdscr.getch()
        return choice

def main(stdscr, args):
    # Initialize viewer state
    state = ViewerState(log=args.log)

    # Initialize ncurses
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)

    # Main loop
    while True:
        key = state.display(stdscr)
        # print key in humman readable form for debugging
        state.print_to_log(f"Key: {key} ({curses.keyname(key)})")
        if not state.handle_key(stdscr, key):
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenAI Model Viewer")
    parser.add_argument('--log', type=str, default=None, help="Log file to write to")

    args = parser.parse_args()

    # Check if the API key is set
    if not openai.api_key:
        raise ValueError("Please set the API key using the OPENAI_API_KEY environment variable.")

    # Run the main function using curses.wrapper to handle errors and cleanup
    curses.wrapper(main, args)
