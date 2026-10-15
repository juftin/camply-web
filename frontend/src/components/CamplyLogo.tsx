import { useTheme } from "@/hooks/use-theme";
import { cn } from "@/lib/utils";

interface CamplyLogoProps {
  className?: string;
  height?: number;
  variant?: "horizontal" | "stacked" | "icon";
}

/** Render the camply artwork with optional title and theme-aware colors. */
export const CamplyLogo = ({
  className,
  height = 40,
  variant = "horizontal",
}: CamplyLogoProps) => {
  const { userTheme } = useTheme();
  const aspectRatio =
    variant === "horizontal"
      ? 1280 / 380
      : 640 / (variant === "stacked" ? 510 : 380);

  return (
    <img
      src={`${import.meta.env.BASE_URL}branding/camply-${variant}${userTheme === "dark" ? "-dark" : ""}.svg`}
      alt="camply"
      width={Math.round(height * aspectRatio)}
      height={height}
      className={cn("block shrink-0 object-contain", className)}
    />
  );
};
