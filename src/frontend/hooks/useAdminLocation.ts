import { useSearchParams } from "react-router-dom";

/** Preserve admin filters and pagination in shareable URLs. */
export function useAdminLocation(pageKey = "page") {
  const [params, setParams] = useSearchParams();
  const rawPage = Number(params.get(pageKey) ?? 0);
  const page = Number.isSafeInteger(rawPage) && rawPage >= 0 ? rawPage : 0;
  const update = (
    values: Record<string, string | number | null>,
    resetPage = true,
  ) => {
    setParams(
      (previous) => {
        const next = new URLSearchParams(previous);
        if (resetPage) next.delete(pageKey);
        Object.entries(values).forEach(([key, value]) => {
          if (value === null || value === "" || value === "all" || value === 0)
            next.delete(key);
          else next.set(key, String(value));
        });
        return next;
      },
      { replace: true },
    );
  };
  return {
    params,
    page,
    update,
    setPage: (value: number) => update({ [pageKey]: value }, false),
  };
}
