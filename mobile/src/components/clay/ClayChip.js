import { Pressable, StyleSheet, Text, View } from "react-native";
import { Shadow } from "react-native-shadow-2";
import { clayShadow, clayRadius, claySurfaceColor } from "@/theme/clay";
import { colors } from "@/theme/colors";

// A selectable pill: raised clay when unselected, flat-filled with the
// accent color (pressed-looking, "chosen") when selected.
export default function ClayChip({ label, selected, onPress }) {
  if (selected) {
    return (
      <Pressable onPress={onPress} style={styles.selected}>
        <Text style={styles.selectedText}>{label}</Text>
      </Pressable>
    );
  }

  return (
    <Pressable onPress={onPress}>
      <Shadow
        distance={clayShadow.darkSubtle.distance}
        startColor={clayShadow.darkSubtle.color}
        offset={clayShadow.darkSubtle.offset}
        style={styles.shadowStyle}
      >
        <Shadow
          distance={clayShadow.lightSubtle.distance}
          startColor={clayShadow.lightSubtle.color}
          offset={clayShadow.lightSubtle.offset}
          style={styles.shadowStyle}
        >
          <View style={styles.chip}>
            <Text style={styles.chipText}>{label}</Text>
          </View>
        </Shadow>
      </Shadow>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  shadowStyle: { borderRadius: clayRadius.pill },
  chip: {
    borderRadius: clayRadius.pill,
    paddingHorizontal: 16,
    paddingVertical: 9,
    backgroundColor: claySurfaceColor,
  },
  chipText: { color: colors.text, fontWeight: "500" },
  selected: {
    borderRadius: clayRadius.pill,
    paddingHorizontal: 16,
    paddingVertical: 9,
    backgroundColor: colors.primary,
  },
  selectedText: { color: "#ffffff", fontWeight: "600" },
});
