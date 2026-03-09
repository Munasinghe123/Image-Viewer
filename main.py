
from views.main_window import MainWindow

if __name__ == "__main__":
    app = MainWindow()
    print("App created")
    
    # app.mainloop()
    # print("Mainloop ended")

    try:
        app.mainloop()
        print("Mainloop ended")
    except KeyboardInterrupt:
        print("Interrupt received — ignoring")