/* SaveFileController
 *
 * Version 1.0
 *
 * November 13, 2017
 *
 * Copyright (c) 2017 Cup Of Java. All rights reserved.
 */

package com.cmput301f17t11.cupofjava.Controllers;

import android.content.Context;

import com.cmput301f17t11.cupofjava.Models.Habit;
import com.cmput301f17t11.cupofjava.Models.HabitEvent;
import com.cmput301f17t11.cupofjava.Models.HabitList;
import com.cmput301f17t11.cupofjava.Models.User;
import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.lang.reflect.Type;
import java.util.ArrayList;

/**
 * Implements the file to save data to.
 *
 * @version 1.0
 */
public class SaveFileController {
    private ArrayList<User> allUsers;
    //private String username;
    private String saveFile = "test_save_file4.sav";

    public SaveFileController(){
            this.allUsers = new ArrayList<User>();
    }

    /**
     * Loads data from file.
     *
     * @param context instance of Context
     */
    private void loadFromFile(Context context){
            try{
                FileInputStream ifStream = context.openFileInput(saveFile);
            BufferedReader bufferedReader = new BufferedReader(new InputStreamReader(ifStream));
            Gson gson = new Gson();
            Type userArrayListType = new TypeToken<ArrayList<User>>(){}.getType();
            this.allUsers = gson.fromJson(bufferedReader, userArrayListType);
            ifStream.close();
        }
        //create a new array list if a file does not already exist
        catch (FileNotFoundException e){
                this.allUsers = new ArrayList<User>();
            saveToFile(context);
        }
        catch (IOException e){
                throw new RuntimeException();
        }
    }

    /**
     * Saves current ArrayList contents in file.
     *
     * @param context instance of Context
     */

    private void saveToFile(Context context){
            try{
                FileOutputStream ofStream = context.openFileOutput(saveFile, Context.MODE_PRIVATE);
            BufferedWriter bufferedWriter = new BufferedWriter(new OutputStreamWriter(ofStream));
            Gson gson = new Gson();
            gson.toJson(this.allUsers, bufferedWriter);
            bufferedWriter.flush();
            ofStream.close();
        }
        catch (FileNotFoundException e){
                //shouldn't really happen, since a file not found would create a new file.
            throw new RuntimeException("Laws of nature defied!");
        }
        catch (IOException e){
                throw new RuntimeException();
        }
    }

    /**
     * Adds new user and saves to file.
     *
     * @param context instance of Context
     * @param user instance of User
     * @see User
     */
    public void addNewUser(Context context, User user){
            loadFromFile(context);
        this.allUsers.add(user);
        saveToFile(context);
    }

    /**
     * Deletes all user from file.
     *
     * @param context instance of Context
     */
    public void deleteAllUsers(Context context){
            this.allUsers = new ArrayList<>();
        saveToFile(context);
    }

    /**
     * Gets user index.
     *
     * @param context instance of Context
     * @param username string username
     * @return integer user index if username matches, -1 otherwise
     */
    public int getUserIndex(Context context, String username){
            loadFromFile(context);
        for (int i = 0; i < this.allUsers.size(); i++){
                if (this.allUsers.get(i).getUsername().equals(username)){
                    return i;
            }
        }
        return -1;
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
     * Gets ArrayList of type Habit.
     *
     * @param context instance of Context
     * @param userIndex integer user index
     * @return list
     */
    public ArrayList<Habit> getHabitListAsArray(Context context, int userIndex){
            loadFromFile(context);
        ArrayList<Habit> list = this.allUsers.get(userIndex).getHabitListAsArray();
        return list;
    }

    /**
     * Adds a habit to a particular user's habit list.
     *
     * @param context instance of Context
     * @param userIndex integer user index
     * @param habit instance of Habit
     * @see Habit
     */
    public void addHabit(Context context, int userIndex, Habit habit){
            loadFromFile(context);

        this.allUsers.get(userIndex).getHabitList().addHabit(habit);
        saveToFile(context);
    }

    /**
     * Gets habit from a particular user's habit list.
     *
     * @param context instance of Context
     * @param userIndex integer user index
     * @param habitIndex integer index of habit
     * @return instance of Habit
     * @see Habit
     */
    public Habit getHabit(Context context, int userIndex, int habitIndex){
            loadFromFile(context);
        return this.allUsers.get(userIndex).getHabitListAsArray().get(habitIndex);
    }

    /**
     * Deletes habit from a certain user's habit list.
     *
     * @param context instance of Context
     * @param userIndex integer user index
     * @param habitIndex integer index of habit
     */
    public void deleteHabit(Context context, int userIndex, int habitIndex){
            loadFromFile(context);
        this.allUsers.get(userIndex).getHabitListAsArray().remove(habitIndex);
        saveToFile(context);
    }

    /**
     * Adds habit event to a particular user's habit event list.
     *
     * @param context instance of Context
     * @param userIndex integer user index
     * @param habitIndex integer index of habit
     * @param habitEvent instance of HabitEvent
     * @see HabitEvent
     */
    public void addHabitEvent(Context context, int userIndex, int habitIndex, HabitEvent habitEvent){
            loadFromFile(context);
        this.allUsers.get(userIndex).getHabitList().getHabit(habitIndex).addHabitEvent(habitEvent);
        saveToFile(context);
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

    /**
     * For use in timeline view.
     *
     * @param context instance of Context
     * @param userIndex integer user index
     * @return ArrayList of HabitEvent type
     * @see HabitEvent
     */
    public ArrayList<HabitEvent> getAllHabitEvents(Context context, int userIndex){
            loadFromFile(context);
        ArrayList<HabitEvent> habitEvents = new ArrayList<>();
        User user = this.allUsers.get(userIndex);
        ArrayList<Habit> habitList = user.getHabitListAsArray();
        Habit currentHabit;
        ArrayList<HabitEvent> currentHabitEvents;
        for (int i = 0; i < habitList.size(); i++){
                currentHabit = habitList.get(i);
            currentHabitEvents = currentHabit.getHabitEventHistory().getHabitEvents();
            for (int j = 0; j < currentHabitEvents.size() ; j++){
                    habitEvents.add(user.getHabitListAsArray().get(i)
                        .getHabitEventHistory().getHabitEvents().get(j));
            }
        }
        return habitEvents;
    }
}
