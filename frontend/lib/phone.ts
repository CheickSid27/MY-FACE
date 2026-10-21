/** Numero au format international lisible : « +2250701020304 » devient
 * « +225 07 01 02 03 04 ». Les autres formats sont rendus tels quels. */
export function formatPhone(phone: string | null | undefined): string {
  if (!phone) return "";
  const ivoirien = /^\+225(\d{10})$/.exec(phone);
  if (ivoirien) return `+225 ${ivoirien[1].replace(/(\d{2})(?=\d)/g, "$1 ")}`;
  return phone;
}
