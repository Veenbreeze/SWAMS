import * as ImagePicker from "expo-image-picker";

const PICKER_OPTIONS = {
  mediaTypes: ["images"],
  allowsEditing: true,
  aspect: [1, 1],
  quality: 0.7,
};

export async function pickProfilePictureFromLibrary() {
  const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
  if (!permission.granted) return null;

  const result = await ImagePicker.launchImageLibraryAsync(PICKER_OPTIONS);
  return result.canceled ? null : result.assets[0];
}

export async function captureProfilePicture() {
  const permission = await ImagePicker.requestCameraPermissionsAsync();
  if (!permission.granted) return null;

  const result = await ImagePicker.launchCameraAsync(PICKER_OPTIONS);
  return result.canceled ? null : result.assets[0];
}
