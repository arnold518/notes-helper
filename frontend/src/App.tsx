import { useState } from "react";
import Home from "./pages/Home";
import ProjectPage from "./pages/ProjectPage";
import "./styles/global.css";

type View = { page: "home" } | { page: "project"; id: string };

export default function App() {
  const [view, setView] = useState<View>({ page: "home" });

  if (view.page === "project") {
    return (
      <ProjectPage
        projectId={view.id}
        onBack={() => setView({ page: "home" })}
      />
    );
  }

  return (
    <Home onOpenProject={(id) => setView({ page: "project", id })} />
  );
}
