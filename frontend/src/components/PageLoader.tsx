import { Component, Suspense, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";

class PageErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div role="alert" className="p-8 text-center space-y-4">
          <p>Unable to load this page. Please reload to try again.</p>
          <Button onClick={() => window.location.reload()}>Reload page</Button>
        </div>
      );
    }
    return this.props.children;
  }
}

export const PageLoader = ({ children }: { children: ReactNode }) => {
  const { pathname } = useLocation();
  return (
    <PageErrorBoundary key={pathname}>
      <Suspense
        fallback={
          <div role="status" className="p-8 text-center">
            Loading page…
          </div>
        }
      >
        {children}
      </Suspense>
    </PageErrorBoundary>
  );
};
