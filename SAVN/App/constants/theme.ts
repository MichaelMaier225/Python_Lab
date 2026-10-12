/**
 * Below are the colors that are used in the app. The colors are defined in the light and dark mode.
 * There are many other ways to style your app. For example, [Nativewind](https://www.nativewind.dev/), [Tamagui](https://tamagui.dev/), [unistyles](https://reactnativeunistyles.vercel.app), etc.
 */

import { Platform } from 'react-native';
import { BrandColors } from './brand';

const tintColorLight = BrandColors.textOnBrand;
const tintColorDark = BrandColors.textOnBrand;

export const Colors = {
  light: {
    text: BrandColors.textOnBrand,
    background: BrandColors.background,
    tint: tintColorLight,
    icon: BrandColors.textOnBrandMuted,
    tabIconDefault: BrandColors.textOnBrandMuted,
    tabIconSelected: tintColorLight,
  },
  dark: {
    text: BrandColors.textOnBrand,
    background: BrandColors.backgroundDark,
    tint: tintColorDark,
    icon: BrandColors.textOnBrandMuted,
    tabIconDefault: BrandColors.textOnBrandMuted,
    tabIconSelected: tintColorDark,
  },
};

export const Fonts = Platform.select({
  ios: {
    /** iOS `UIFontDescriptorSystemDesignDefault` */
    sans: 'system-ui',
    /** iOS `UIFontDescriptorSystemDesignSerif` */
    serif: 'ui-serif',
    /** iOS `UIFontDescriptorSystemDesignRounded` */
    rounded: 'ui-rounded',
    /** iOS `UIFontDescriptorSystemDesignMonospaced` */
    mono: 'ui-monospace',
  },
  default: {
    sans: 'normal',
    serif: 'serif',
    rounded: 'normal',
    mono: 'monospace',
  },
  web: {
    sans: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    serif: "Georgia, 'Times New Roman', serif",
    rounded: "'SF Pro Rounded', 'Hiragino Maru Gothic ProN', Meiryo, 'MS PGothic', sans-serif",
    mono: "SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
  },
});
