import { View } from "react-native";
import { Shadow } from "react-native-shadow-2";
import { clayRadius, clayShadow, clayInsetShadow, claySurfaceColor } from "@/theme/clay";

// A raised (or, with `inset`, pressed-in) clay panel. `style` positions the
// whole surface (margin, width, flex); `contentStyle` styles the inner
// content box (padding, gap) since that's the View that actually carries
// the background color and clips children.
export default function ClaySurface({
  children,
  radius = clayRadius.md,
  backgroundColor = claySurfaceColor,
  inset = false,
  subtle = false,
  stretch = true,
  style,
  contentStyle,
}) {
  if (inset) {
    return (
      <Shadow
        distance={clayInsetShadow.distance}
        startColor={clayInsetShadow.color}
        offset={clayInsetShadow.offset}
        paintInside
        stretch={stretch}
        style={{ borderRadius: radius }}
        containerStyle={style}
      >
        <View style={[{ borderRadius: radius, backgroundColor, overflow: "hidden" }, contentStyle]}>
          {children}
        </View>
      </Shadow>
    );
  }

  const dark = subtle ? clayShadow.darkSubtle : clayShadow.dark;
  const light = subtle ? clayShadow.lightSubtle : clayShadow.light;

  return (
    <Shadow
      distance={dark.distance}
      startColor={dark.color}
      offset={dark.offset}
      stretch={stretch}
      style={{ borderRadius: radius }}
      containerStyle={style}
    >
      <Shadow
        distance={light.distance}
        startColor={light.color}
        offset={light.offset}
        stretch={stretch}
        style={{ borderRadius: radius }}
      >
        <View style={[{ borderRadius: radius, backgroundColor }, contentStyle]}>{children}</View>
      </Shadow>
    </Shadow>
  );
}
