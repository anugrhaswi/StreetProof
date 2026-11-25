import AdminLayout from '../../components/admin/AdminLayout';

interface PlaceholderPageProps {
  title: string;
  description: string;
}

export default function PlaceholderPage({ title, description }: PlaceholderPageProps) {
  return (
    <AdminLayout title={title}>
      <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-8 text-center max-w-2xl">
        <h2 className="text-lg font-medium text-white mb-2">{title}</h2>
        <p className="text-gray-400 text-sm">{description}</p>
      </div>
    </AdminLayout>
  );
}
