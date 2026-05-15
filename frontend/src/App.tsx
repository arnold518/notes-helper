import { useState } from "react";
import Home from "./pages/Home";
import ProjectPage from "./pages/ProjectPage";
import SubjectPage from "./pages/SubjectPage";
import "./styles/global.css";

type View =
  | { page: "home" }
  | { page: "subject"; id: string }
  | { page: "project"; id: string; subjectId?: string };

export default function App() {
  const [view, setView] = useState<View>({ page: "home" });

  if (view.page === "project") {
    return (
      <ProjectPage
        projectId={view.id}
        onBack={() => view.subjectId
          ? setView({ page: "subject", id: view.subjectId })
          : setView({ page: "home" })}
      />
    );
  }

  if (view.page === "subject") {
    return (
      <SubjectPage
        subjectId={view.id}
        onBack={() => setView({ page: "home" })}
        onOpenProject={(projectId) => setView({ page: "project", id: projectId, subjectId: view.id })}
      />
    );
  }

  return (
    <Home onOpenSubject={(id) => setView({ page: "subject", id })} />
  );
}
