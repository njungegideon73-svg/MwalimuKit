export function PrivacyPolicyPage() {
  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Privacy Policy</h1>
      <p className="text-sm text-gray-500">Last updated: August 2026</p>

      <div className="card space-y-4">
        <h2 className="font-semibold text-gray-900">What we collect</h2>
        <p className="text-sm text-gray-600">
          MwalimuKit collects only the minimum data needed to provide the service:
        </p>
        <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
          <li>Teacher account information (name, email)</li>
          <li>School identification (school code)</li>
          <li>Learner names, optional admission numbers, and optional gender</li>
          <li>Assessment content you create or generate</li>
          <li>Score entries you record</li>
        </ul>
      </div>

      <div className="card space-y-4">
        <h2 className="font-semibold text-gray-900">How we use your data</h2>
        <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
          <li>To provide the assessment and scoring service</li>
          <li>To sync your data across your devices</li>
          <li>To generate AI assessments (only strand labels and teacher prompts are sent to the AI provider)</li>
        </ul>
      </div>

      <div className="card space-y-4">
        <h2 className="font-semibold text-gray-900">What we never do</h2>
        <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
          <li>We never send learner names, scores, or school identifiers to AI providers</li>
          <li>We never sell or share your data with third parties</li>
          <li>We never show learner information to anyone outside their school</li>
        </ul>
      </div>

      <div className="card space-y-4">
        <h2 className="font-semibold text-gray-900">Data storage</h2>
        <p className="text-sm text-gray-600">
          Your data is stored securely in encrypted databases. The web app also stores data locally
          in your browser (IndexedDB) for offline access. Signing out clears all local data.
        </p>
      </div>

      <div className="card space-y-4">
        <h2 className="font-semibold text-gray-900">Your rights</h2>
        <p className="text-sm text-gray-600">
          You can export all your data at any time from Settings. You can request deletion of your
          school data by contacting the platform administrator.
        </p>
      </div>
    </div>
  );
}
