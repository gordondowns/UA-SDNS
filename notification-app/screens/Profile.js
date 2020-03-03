import React, { Component } from "react";
import {
    View,
    Image,
    Text,
    StyleSheet,
    ScrollView
} from "react-native";

class Profile extends Component {
    render() {
        return (
            <View style={{alignItems: "center", justifyContent: "center", flex: 1}}> 
              <Image
                source={require('../assets/testImage.jpg')} //Imports the image directly from the "assets" folder.
                style={{width: 333, height: 250, borderWidth: 1}} //Original aspect ratio of 640 X 480.
              />
              <Text style={{fontSize: 14, fontFamily: 'lucida grande'}}>
                Recent activity
              </Text>  
            </View>
        );
    } 
}
export default Profile;