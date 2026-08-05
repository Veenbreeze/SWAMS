// Claymorphism tokens: big radii + soft dual-tone (light/dark) shadows so
// surfaces read as puffy, extruded plastic rather than flat material cards.
// Shadow tones are tuned against colors.background (#eaf2fb, a pale blue)
// so raised surfaces look lifted off it and inset ones look pressed in.
export const clayRadius = {
  sm: 16,
  md: 22,
  lg: 28,
  pill: 999,
};

// A shade lighter than colors.background so clay surfaces read as "risen"
// off the page rather than blending flat into it.
export const claySurfaceColor = "#f8fbff";

// Raised (default) shadow pair: light shadow up-left, dark shadow down-right.
// Used by ClaySurface/ClayButton/ClayIconBadge for cards, buttons, badges.
export const clayShadow = {
  light: { color: "#ffffff", offset: [-7, -7], distance: 11 },
  dark: { color: "rgba(148, 163, 184, 0.55)", offset: [7, 7], distance: 11 },
  // Smaller-footprint version for chips/pills that shouldn't float as high
  // as full cards.
  lightSubtle: { color: "#ffffff", offset: [-3, -3], distance: 6 },
  darkSubtle: { color: "rgba(148, 163, 184, 0.5)", offset: [3, 3], distance: 6 },
  // Squished-in variant ClayButton switches to on press, for tactile feedback.
  lightPressed: { color: "#ffffff", offset: [-2, -2], distance: 3 },
  darkPressed: { color: "rgba(148, 163, 184, 0.5)", offset: [2, 2], distance: 3 },
};

// Single soft inward shadow for "pressed into the clay" surfaces, like
// text inputs and the floating tab bar.
export const clayInsetShadow = { color: "rgba(30, 41, 59, 0.16)", offset: [3, 3], distance: 7 };
