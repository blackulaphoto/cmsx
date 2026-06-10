import { useMemo, useState } from "react";
import { MapPin } from "lucide-react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { type LocationOption, searchLocationOptions } from "./locations";

type LocationInputProps = {
  value: string;
  placeholder?: string;
  className?: string;
  onValueChange: (value: string) => void;
  onOptionSelect?: (option: LocationOption) => void;
};

export function LocationInput({
  value,
  placeholder = "Search city or state",
  className,
  onValueChange,
  onOptionSelect,
}: LocationInputProps) {
  const [isOpen, setIsOpen] = useState(false);
  const matches = useMemo(() => searchLocationOptions(value, 8), [value]);

  return (
    <div className="relative">
      <MapPin className="pointer-events-none absolute left-3 top-1/2 z-10 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        value={value}
        placeholder={placeholder}
        className={cn("pl-9", className)}
        onFocus={() => setIsOpen(true)}
        onBlur={() => {
          window.setTimeout(() => setIsOpen(false), 120);
        }}
        onChange={(event) => {
          onValueChange(event.target.value);
          setIsOpen(true);
        }}
      />
      {isOpen && matches.length > 0 ? (
        <div className="absolute left-0 right-0 top-[calc(100%+0.5rem)] z-40 overflow-hidden rounded-2xl border border-border/60 bg-popover shadow-xl">
          <div className="max-h-72 overflow-y-auto p-2">
            {matches.map((option) => (
              <button
                key={`${option.city}-${option.regionCode}`}
                type="button"
                className="flex w-full items-center justify-between rounded-xl px-3 py-3 text-left text-sm transition-colors hover:bg-accent hover:text-accent-foreground"
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => {
                  onValueChange(option.label);
                  onOptionSelect?.(option);
                  setIsOpen(false);
                }}
              >
                <span className="font-medium">{option.label}</span>
                <span className="text-xs text-muted-foreground">{option.regionCode}</span>
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
