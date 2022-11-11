/**
 * Implements the file to save data to.
 *
 * @version 1.0
 */
public class SaveFileController extends SudoUser {
    private ArrayList<User> allUsers;
    //private String username;
    private String saveFile = "test_save_file4.sav";

    public SaveFileController(){
            this.allUsers = new ArrayList<User>();
    }

    /**
     * Gets HabitList instance.
     *
     * @param context instance of Context
     * @param userIndex integer user index
     * @return HabitList
     * @see HabitList
     */
    public HabitList getHabitList(Context context, int userIndex){
            loadFromFile(context);
        return this.allUsers.get(userIndex).getHabitList();
    }

    /**
     * Removes a habit event from a particular user's habit event list.
     *
     * @param context instance of Context
     * @param userIndex integer user index
     * @param habitIndex integer index of habit
     * @param habitEventIndex integer index of habit event
     */
    public void removeHabitEvent(Context context, int userIndex, int habitIndex, int habitEventIndex){
            loadFromFile(context);
        this.allUsers.get(userIndex).getHabitList().getHabit(habitIndex)
                .getHabitEventHistory().getHabitEvents().remove(habitEventIndex);
        saveToFile(context);
    }
}
