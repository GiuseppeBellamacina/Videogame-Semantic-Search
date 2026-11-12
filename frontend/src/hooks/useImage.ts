import { useEffect, useState } from "react";
import { peekImage, requestImage } from "@/lib/imageQueue";

/** Picture for an entity: url when found, null when there is none, undefined while loading. */
export function useImage(type: string, name: string, urgent = false) {
  const [url, setUrl] = useState<string | null | undefined>(() =>
    peekImage(type, name),
  );
  useEffect(() => {
    let live = true;
    const known = peekImage(type, name);
    if (known !== undefined) setUrl(known);
    else {
      setUrl(undefined);
      requestImage(type, name, urgent).then((u) => live && setUrl(u));
    }
    return () => {
      live = false;
    };
  }, [type, name, urgent]);
  return url;
}
