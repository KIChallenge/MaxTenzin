import { redirect } from "next/navigation";

/** Vollmachten moved into Einstellungen. */
export default function VertretungRedirect() {
  redirect("/einstellungen#vollmachten");
}
