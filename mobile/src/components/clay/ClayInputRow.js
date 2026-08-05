import { View, StyleSheet } from "react-native";
import { Shadow } from "react-native-shadow-2";
import { clayRadius, clayInsetShadow, claySurfaceColor } from "@/theme/clay";

// A "pressed into the clay" row for text inputs — icon + TextInput +
// optional trailing accessory are passed as children.
export default function ClayInputRow({ children, radius = clayRadius.sm, style, multiline = false }) {
  return (
    <Shadow
      distance={clayInsetShadow.distance}
      startColor={clayInsetShadow.color}
      offset={clayInsetShadow.offset}
      paintInside
      stretch
      style={{ borderRadius: radius }}
      containerStyle={style}
    >
      <View
        style={[
          styles.row,
          multiline && styles.multiline,
          { borderRadius: radius, backgroundColor: claySurfaceColor },
        ]}
      >
        {children}
      </View>
    </Shadow>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    minHeight: 48,
  },
  multiline: { alignItems: "flex-start", paddingVertical: 12 },
});
