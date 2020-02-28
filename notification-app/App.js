//Importing libraries
import React from 'react';
import { StyleSheet, Text, View, Image } from 'react-native';

import { createBottomTabNavigator } from 'react-navigation'
import Icon from 'react-native-vector-icons/Ionicons'
import Profile from './screens/Profile'
import Logs from './screens/Logs'
import Options from './screens/Options'

//Exports the bottom tab navigator to the project.
export default createBottomTabNavigator({
    Profile: {
    screen: Profile,
    navigationOptions: {
      tabBarLabel: 'PROFILE',
      tabBarIcon: ({ tintColor }) => (
        <Image source={require('./assets/profile.png')} style={{ height: 24, width: 24, tintColor: tintColor }} />
      )
    }
  },
  Logs: {
    screen: Logs,
    navigationOptions: {
      tabBarLabel: 'LOGS',
      tabBarIcon: ({ tintColor }) => (
        <Image source={require('./assets/logs.png')} style={{ height: 24, width: 24, tintColor: tintColor }} />
      )
    } 
  },
  Options: {
    screen: Options,
    navigationOptions: {
      tabBarLabel: 'OPTIONS',
      tabBarIcon: ({ tintColor }) => (
        <Image source={require('./assets/options.png')} style={{ height: 24, width: 24, tintColor: tintColor }} />
      )
    }
  }, 

}, {
    tabBarOptions: {
      activeTintColor: 'red', //When button is selected, the color will shift to red
      inactiveTintColor: 'black',
      style: {
        backgroundColor: 'white',
        borderTopWidth: 0,
        shadowOffset: { width: 5, height: 3 },
        shadowColor: 'black',
        shadowOpacity: 0.5,
        elevation: 5
      }
    }
  })