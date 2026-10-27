# Records the revenant demo. Run: demo/record.sh
Output demo/revenant-demo.gif
Set Shell "zsh"
Set FontSize 16
Set Width 1200
Set Height 640
Set Padding 20
Set TypingSpeed 60ms
Set Theme "Dracula"

Hide
Type "source $REVENANT_SRC/demo/zdot/.zshrc && cd $REVENANT_SRC/demo/stage && clear"
Enter
Sleep 1s
Show

Type "# a shell with a Ghost. These are stand-in commands; the history is fabricated."
Enter
Sleep 1.5s

Type "ls"
Enter
Sleep 1.5s

Type "docker compose up"
Enter
Sleep 7s

Type "git push --force origin main"
Enter
Sleep 7s

Type "make test"
Enter
Sleep 1.5s
Type "make test"
Enter
Sleep 7s

Type "revenant stats"
Enter
Sleep 4s
Screenshot demo/shot-end.png

Type "revenant off"
Enter
Sleep 1s
Type "docker compose up"
Enter
Sleep 6s
Type "# off means off: nothing was whispered above."
Enter
Sleep 2s
