import { useState } from 'react';
import { School, Plus, Search, Edit, Trash2 } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import { Modal } from '@/components/Modal';

interface SchoolData {
  id: string;
  name: string;
  code: string;
  county: string | null;
  level: string | null;
  created_at: string;
}

interface SchoolForm {
  name: string;
  code: string;
  county: string;
  level: string;
}

export function SchoolsManagementPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingSchool, setEditingSchool] = useState<SchoolData | null>(null);
  const [formData, setFormData] = useState<SchoolForm>({
    name: '',
    code: '',
    county: '',
    level: '',
  });

  const { data: schools, isLoading } = useQuery<SchoolData[]>({
    queryKey: ['super-admin-schools', search],
    queryFn: () => apiFetch(`/super-admin/schools?search=${search}`),
  });

  const createMutation = useMutation({
    mutationFn: (data: SchoolForm) =>
      apiFetch('/super-admin/schools', { method: 'POST', json: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['super-admin-schools'] });
      setShowCreateModal(false);
      resetForm();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: SchoolForm }) =>
      apiFetch(`/super-admin/schools/${id}`, { method: 'PATCH', json: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['super-admin-schools'] });
      setEditingSchool(null);
      resetForm();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/super-admin/schools/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['super-admin-schools'] });
    },
  });

  const resetForm = () => {
    setFormData({ name: '', code: '', county: '', level: '' });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingSchool) {
      updateMutation.mutate({ id: editingSchool.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const handleEdit = (school: SchoolData) => {
    setEditingSchool(school);
    setFormData({
      name: school.name,
      code: school.code,
      county: school.county || '',
      level: school.level || '',
    });
    setShowCreateModal(true);
  };

  const handleDelete = (id: string) => {
    if (confirm('Are you sure you want to delete this school? This action cannot be undone.')) {
      deleteMutation.mutate(id);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-blue-50 flex items-center justify-center">
            <School className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Schools Management</h1>
            <p className="text-sm text-gray-500">Add, edit, or remove schools from the system</p>
          </div>
        </div>
        <button
          onClick={() => {
            resetForm();
            setEditingSchool(null);
            setShowCreateModal(true);
          }}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          Add School
        </button>
      </div>

      {/* Search */}
      <div className="card">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search schools..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input pl-10 w-full"
          />
        </div>
      </div>

      {/* Schools List */}
      <div className="card">
        {isLoading ? (
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-16 bg-gray-100 rounded-lg animate-pulse" />
            ))}
          </div>
        ) : schools?.length === 0 ? (
          <div className="text-center py-8">
            <School className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No schools found</p>
          </div>
        ) : (
          <div className="space-y-2">
            {schools?.map((school) => (
              <div
                key={school.id}
                className="flex items-center justify-between p-4 rounded-lg border border-gray-100 hover:border-gray-200"
              >
                <div className="flex items-center gap-4">
                  <div className="h-10 w-10 rounded-lg bg-primary-50 flex items-center justify-center">
                    <span className="text-primary-700 font-medium text-sm">
                      {school.name.charAt(0)}
                    </span>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{school.name}</p>
                    <p className="text-sm text-gray-500">
                      Code: {school.code} • {school.county || 'No county'} • {school.level || 'No level'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleEdit(school)}
                    className="p-2 text-gray-400 hover:text-primary-600 hover:bg-primary-50 rounded-lg"
                  >
                    <Edit className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(school.id)}
                    className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create/Edit Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => {
          setShowCreateModal(false);
          setEditingSchool(null);
          resetForm();
        }}
        title={editingSchool ? 'Edit School' : 'Add New School'}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              School Name *
            </label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="input w-full"
              placeholder="Enter school name"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              School Code *
            </label>
            <input
              type="text"
              required
              value={formData.code}
              onChange={(e) => setFormData({ ...formData, code: e.target.value })}
              className="input w-full"
              placeholder="Enter school code (4-16 characters)"
              minLength={4}
              maxLength={16}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              County
            </label>
            <input
              type="text"
              value={formData.county}
              onChange={(e) => setFormData({ ...formData, county: e.target.value })}
              className="input w-full"
              placeholder="Enter county"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Level
            </label>
            <select
              value={formData.level}
              onChange={(e) => setFormData({ ...formData, level: e.target.value })}
              className="input w-full"
            >
              <option value="">Select level</option>
              <option value="primary">Primary</option>
              <option value="secondary">Secondary</option>
              <option value="tertiary">Tertiary</option>
            </select>
          </div>
          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={() => {
                setShowCreateModal(false);
                setEditingSchool(null);
                resetForm();
              }}
              className="btn-secondary"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending || updateMutation.isPending}
              className="btn-primary"
            >
              {createMutation.isPending || updateMutation.isPending
                ? 'Saving...'
                : editingSchool
                ? 'Update School'
                : 'Create School'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
