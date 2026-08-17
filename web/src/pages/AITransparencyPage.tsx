import { Shield, Eye, Brain, Lock } from 'lucide-react';

export function AITransparencyPage() {
  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">AI Transparency</h1>
        <p className="text-gray-500 text-sm mt-1">
          How MwalimuKit uses artificial intelligence
        </p>
      </div>

      <div className="card space-y-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-blue-50 flex items-center justify-center">
            <Brain className="h-5 w-5 text-blue-600" />
          </div>
          <h2 className="font-semibold text-gray-900">What the AI does</h2>
        </div>
        <p className="text-sm text-gray-600">
          When you choose "AI draft" mode, MwalimuKit sends a request to an AI provider
          (OpenAI or Anthropic) to generate assessment items and rubrics aligned to the
          Kenyan Competency-Based Curriculum (CBC).
        </p>
      </div>

      <div className="card space-y-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-green-50 flex items-center justify-center">
            <Eye className="h-5 w-5 text-green-600" />
          </div>
          <h2 className="font-semibold text-gray-900">What the AI sees</h2>
        </div>
        <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
          <li>The learning area, strand, and sub-strand label (e.g. "Numbers", "Counting 0 to 20")</li>
          <li>The grade level</li>
          <li>Any guidance you type in the "Teacher guidance" box</li>
        </ul>
      </div>

      <div className="card space-y-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-red-50 flex items-center justify-center">
            <Lock className="h-5 w-5 text-red-600" />
          </div>
          <h2 className="font-semibold text-gray-900">What the AI never sees</h2>
        </div>
        <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
          <li>Learner names or any personally identifiable information</li>
          <li>Assessment scores or grades</li>
          <li>School names or identifiers</li>
          <li>Teacher email or account information</li>
        </ul>
      </div>

      <div className="card space-y-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-amber-50 flex items-center justify-center">
            <Shield className="h-5 w-5 text-amber-600" />
          </div>
          <h2 className="font-semibold text-gray-900">Your control</h2>
        </div>
        <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
          <li>AI generation is always optional — you can use "Structured template" mode instead</li>
          <li>AI-generated items are clearly labelled "AI" until you save them</li>
          <li>You are the final author — you can edit, delete, or replace any AI-generated content</li>
          <li>School administrators can disable AI generation entirely via feature flags</li>
        </ul>
      </div>
    </div>
  );
}
