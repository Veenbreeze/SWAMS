import { useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { Shadow } from "react-native-shadow-2";
import { clayRadius, clayShadow } from "@/theme/clay";
import { colors } from "@/theme/colors";

const VARIANTS = {
  primary: { background: colors.primary, text: "#ffffff" },
  secondary: { background: colors.secondary, text: "#ffffff" },
  danger: { background: colors.danger, text: "#ffffff" },
};

// A clay "button": raised by default, squishes into the surface (smaller,
// tighter dual shadow) while pressed for tactile feedback.
export default function ClayButton({
  title,
  onPress,
  icon,
  loading = false,
  disabled = false,
  variant = "primary",
  radius = clayRadius.md,
  compact = false,
  style,
}) {
  const [pressed, setPressed] = useState(false);
  const { background, text } = VARIANTS[variant] ?? VARIANTS.primary;
  const busy = loading || disabled;
  const dark = pressed ? clayShadow.darkPressed : clayShadow.dark;
  const light = pressed ? clayShadow.lightPressed : clayShadow.light;

  return (
    <Pressable
      onPress={onPress}
      disabled={busy}
      onPressIn={() => setPressed(true)}
      onPressOut={() => setPressed(false)}
      style={[style, busy && styles.disabled]}
    >
      <Shadow
        distance={dark.distance}
        startColor={dark.color}
        offset={dark.offset}
        stretch
        style={{ borderRadius: radius }}
      >
        <Shadow
          distance={light.distance}
          startColor={light.color}
          offset={light.offset}
          stretch
          style={{ borderRadius: radius }}
        >
          <View
            style={[
              styles.button,
              compact && styles.buttonCompact,
              { backgroundColor: background, borderRadius: radius },
            ]}
          >
            {loading ? (
              <ActivityIndicator color={text} />
            ) : (
              <>
                {icon}
                <Text style={[styles.buttonText, compact && styles.buttonTextCompact, { color: text }]}>
                  {title}
                </Text>
              </>
            )}
          </View>
        </Shadow>
      </Shadow>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  disabled: { opacity: 0.6 },
  button: {
    flexDirection: "row",
    paddingVertical: 14,
    paddingHorizontal: 20,
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  buttonCompact: { paddingVertical: 8, paddingHorizontal: 14, gap: 4 },
  buttonText: { fontWeight: "600", fontSize: 16 },
  buttonTextCompact: { fontSize: 13 },
});
