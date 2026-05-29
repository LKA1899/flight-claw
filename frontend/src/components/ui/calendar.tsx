import { Input } from "@/components/ui/input";

export function Calendar(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <Input type="date" {...props} />;
}
