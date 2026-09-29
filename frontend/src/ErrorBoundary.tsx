import { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error caught by ErrorBoundary:", error, errorInfo);
  }

  private handleReset = async () => {
    try {
      localStorage.clear();
      sessionStorage.clear();
      if ("serviceWorker" in navigator) {
        const registrations = await navigator.serviceWorker.getRegistrations();
        for (const reg of registrations) {
          await reg.unregister();
        }
      }
    } catch {
      // Ignore
    }
    window.location.href = "/";
  };

  public render() {
    if (this.state.hasError) {
      return (
        <main className="boot-screen" style={{ minHeight: "100vh", display: "grid", placeItems: "center" }}>
          <section className="splash-card" style={{ maxWidth: "480px", textAlign: "center", padding: "36px 28px" }}>
            <div className="splash-mark" style={{ margin: "0 auto 12px" }}>
              <img src="/static/pwa-192.png" alt="" />
            </div>
            <h1 style={{ margin: "0 0 8px", fontSize: "24px", color: "#f1f7f3" }}>Session Restored</h1>
            <p style={{ margin: "0 0 16px", color: "rgba(185, 210, 195, 0.75)", fontSize: "14px" }}>
              {this.state.error?.message || "An unexpected interface error occurred. Refreshing the workspace will reconnect your session."}
            </p>
            <div style={{ display: "flex", gap: "12px", justifyContent: "center" }}>
              <button
                className="primary-btn"
                style={{ padding: "10px 20px" }}
                onClick={() => window.location.reload()}
                type="button"
              >
                Reload Workspace
              </button>
              <button
                className="text-btn"
                style={{ padding: "10px 16px" }}
                onClick={this.handleReset}
                type="button"
              >
                Clear Cache & Sign In
              </button>
            </div>
          </section>
        </main>
      );
    }

    return this.props.children;
  }
}
