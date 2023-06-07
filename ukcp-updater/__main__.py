import curses

# Create a window
stdscr = curses.initscr()

# Turn off echoing of keys and enable special keys
curses.noecho()
stdscr.keypad(True)

# Clear the screen
stdscr.clear()

# Print a menu
stdscr.addstr(0, 0, "1. Option 1")
stdscr.addstr(1, 0, "2. Option 2")
stdscr.addstr(2, 0, "3. Option 3")
stdscr.refresh()

# Get user input
while True:
    key = stdscr.getch()
    if key == ord('1'):
        # Handle option 1
        break
    elif key == ord('2'):
        # Handle option 2
        break
    elif key == ord('3'):
        # Handle option 3
        break

# Clean up
curses.keypad(False)
curses.echo()
curses.endwin()