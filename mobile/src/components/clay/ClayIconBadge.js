import { View } from "react-native";
import { Shadow } from "react-native-shadow-2";
import { clayShadow } from "@/theme/clay";
import { colors } from "@/theme/colors";

// A raised circular clay badge, used for the login logo, avatar
// placeholders, and standalone icon accents.
export default function ClayIconBadge({
  children,
  size = 72,
  backgroundColor = colors.primary,
  subtle = false,
  style,
}) {
  const radius = size / 2;
  const dark = subtle ? clayShadow.darkSubtle : clayShadow.dark;
  const light = subtle ? clayShadow.lightSubtle : clayShadow.light;

  return (
    <Shadow
      distance={dark.distance}
      startColor={dark.color}
      offset={dark.offset}
      style={{ borderRadius: radius }}
      containerStyle={style}
    >
      <Shadow
        distance={light.distance}
        startColor={light.color}
        offset={light.offset}
        style={{ borderRadius: radius }}
      >
        <View
          style={{
            width: size,
            height: size,
            borderRadius: radius,
            backgroundColor,
            alignItems: "center",
            justifyContent: "center",
            overflow: "hidden",
          }}
        >
          {children}
        </View>
      </Shadow>
    </Shadow>
  );
}
