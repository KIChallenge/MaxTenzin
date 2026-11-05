"use client";
// Picker for plain GET forms (server pages): keeps its own state, submits via the hidden input.
import { useState } from "react";
import { Picker, type PickerOption } from "./Picker";

export function FormPicker(props: { name: string; label: string; options: PickerOption[]; defaultValue: string; className?: string; emptyLabel?: string }) {
  const [v, setV] = useState(props.defaultValue);
  return <Picker name={props.name} label={props.label} options={props.options} value={v} onChange={setV} className={props.className} emptyLabel={props.emptyLabel} />;
}
