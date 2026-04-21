import { AgentStepViewer } from "@/components/agents/agent-step-viewer";
import { ResultPanel } from "@/components/agents/result-panel";

type CasePageProps = {
  params: Promise<{ id: string }>;
};

export default async function CaseDetailPage({ params }: CasePageProps) {
  const { id } = await params;

  return (
    <main>
      <h1>Case {id}</h1>
      <p>Agent outputs + brief placeholder.</p>
      <AgentStepViewer />
      <ResultPanel />
    </main>
  );
}
