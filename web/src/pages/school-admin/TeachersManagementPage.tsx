import { useState } from 'react';
import { Users, Plus, Search, Edit, Trash2 } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import { Modal } from '@/components/Modal';

interface TeacherData {
  id: string;
  school_id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

interface TeacherForm {
  full_name: string;
  email: string;
  password: string;
}

export function TeachersManagementPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingTeacher, setEditingTeacher] = useState<TeacherData | null>(null);
  const [formData, setFormData] = useState<TeacherForm>({
    full_name: '',
    email: '',
    password: '',
  });

  const { data: teachers, isLoading } = useQuery<TeacherData[]>({
    queryKey: ['school-admin-teachers', search],
    queryFn: () => {
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      return apiFetch(`/school-admin/teachers?${params.toString()}`);
    },
  });

  const createMutation = useMutation({
    mutationFn: (data: TeacherForm) =>
      apiFetch('/school-admin/teachers', { method: 'POST', json: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['school-admin-teachers'] });
      setShowCreateModal(false);
      resetForm();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<TeacherForm> }) =>
      apiFetch(`/school-admin/teachers/${id}`, { method: 'PATCH', json: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['school-admin-teachers'] });
      setEditingTeacher(null);
      resetForm();
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/school-admin/teachers/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['school-admin-teachers'] });
    },
  });

  const resetForm = () => {
    setFormData({ full_name: '', email: '', password: '' });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingTeacher) {
      updateMutation.mutate({ id: editingTeacher.id, data: { full_name: formData.full_name } });
    } else {
      createMutation.mutate(formData);
    }
  };

  const handleEdit = (teacher: TeacherData) => {
    setEditingTeacher(teacher);
    setFormData({
      full_name: teacher.full_name,
      email: teacher.email,
      password: '',
    });
    setShowCreateModal(true);
  };

  const handleDeactivate = (id: string) => {
    if (confirm('Are you sure you want to deactivate this teacher?')) {
      deactivateMutation.mutate(id);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-blue-50 flex items-center justify-center">
            <Users className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Teachers Management</h1>
            <p className="text-sm text-gray-500">Add, edit, or remove teachers from your school</p>
          </div>
        </div>
        <button
          onClick={() => {
            resetForm();
            setEditingTeacher(null);
            setShowCreateModal(true);
          }}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          Add Teacher
        </button>
      </div>

      {/* Search */}
      <div className="card">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search teachers..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input pl-10 w-full"
          />
        </div>
      </div>

      {/* Teachers List */}
      <div className="card">
        {isLoading ? (
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-16 bg-gray-100 rounded-lg animate-pulse" />
            ))}
          </div>
        ) : teachers?.length === 0 ? (
          <div className="text-center py-8">
            <Users className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No teachers found</p>
          </div>
        ) : (
          <div className="space-y-2">
            {teachers?.map((teacher) => (
              <div
                key={teacher.id}
                className="flex items-center justify-between p-4 rounded-lg border border-gray-100 hover:border-gray-200"
              >
                <div className="flex items-center gap-4">
                  <div className="h-10 w-10 rounded-full bg-primary-100 flex items-center justify-center">
                    <span className="text-primary-700 font-medium text-sm">
                      {teacher.full_name.charAt(0)}
                    </span>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{teacher.full_name}</p>
                    <p className="text-sm text-gray-500">{teacher.email}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${teacher.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                    {teacher.is_active ? 'Active' : 'Inactive'}
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleEdit(teacher)}
                      className="p-2 text-gray-400 hover:text-primary-600 hover:bg-primary-50 rounded-lg"
                    >
                      <Edit className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDeactivate(teacher.id)}
                      className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
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
          setEditingTeacher(null);
          resetForm();
        }}
        title={editingTeacher ? 'Edit Teacher' : 'Add New Teacher'}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Full Name *
            </label>
            <input
              type="text"
              required
              value={formData.full_name}
              onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              className="input w-full"
              placeholder="Enter full name"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email *
            </label>
            <input
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="input w-full"
              placeholder="Enter email address"
              disabled={!!editingTeacher}
            />
          </div>
          {!editingTeacher && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Password *
              </label>
              <input
                type="password"
                required
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="input w-full"
                placeholder="Enter password"
                minLength={8}
              />
            </div>
          )}
          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={() => {
                setShowCreateModal(false);
                setEditingTeacher(null);
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
                : editingTeacher
                ? 'Update Teacher'
                : 'Create Teacher'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
