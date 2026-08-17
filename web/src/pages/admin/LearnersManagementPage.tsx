import { useState } from 'react';
import { GraduationCap, Plus, Search, Edit, Trash2 } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import { Modal } from '@/components/Modal';

interface LearnerData {
  id: string;
  school_id: string;
  class_id: string;
  full_name: string;
  admission_no: string | null;
  gender: string | null;
  deleted_at: string | null;
}

interface LearnerForm {
  full_name: string;
  school_id: string;
  class_id: string;
  admission_no: string;
  gender: string;
}

export function LearnersManagementPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [schoolFilter, setSchoolFilter] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingLearner, setEditingLearner] = useState<LearnerData | null>(null);
  const [formData, setFormData] = useState<LearnerForm>({
    full_name: '',
    school_id: '',
    class_id: '',
    admission_no: '',
    gender: '',
  });

  const { data: learners, isLoading } = useQuery<LearnerData[]>({
    queryKey: ['super-admin-learners', search, schoolFilter],
    queryFn: () => {
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (schoolFilter) params.append('school_id', schoolFilter);
      return apiFetch(`/super-admin/learners?${params.toString()}`);
    },
  });

  const { data: schools } = useQuery<{ id: string; name: string; code: string }[]>({
    queryKey: ['super-admin-schools-list'],
    queryFn: () => apiFetch('/super-admin/schools?limit=200'),
  });

  const createMutation = useMutation({
    mutationFn: (data: LearnerForm) =>
      apiFetch('/super-admin/learners', { method: 'POST', json: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['super-admin-learners'] });
      setShowCreateModal(false);
      resetForm();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<LearnerForm> }) =>
      apiFetch(`/super-admin/learners/${id}`, { method: 'PATCH', json: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['super-admin-learners'] });
      setEditingLearner(null);
      resetForm();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/super-admin/learners/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['super-admin-learners'] });
    },
  });

  const resetForm = () => {
    setFormData({ full_name: '', school_id: '', class_id: '', admission_no: '', gender: '' });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingLearner) {
      updateMutation.mutate({ id: editingLearner.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const handleEdit = (learner: LearnerData) => {
    setEditingLearner(learner);
    setFormData({
      full_name: learner.full_name,
      school_id: learner.school_id,
      class_id: learner.class_id,
      admission_no: learner.admission_no || '',
      gender: learner.gender || '',
    });
    setShowCreateModal(true);
  };

  const handleDelete = (id: string) => {
    if (confirm('Are you sure you want to delete this learner?')) {
      deleteMutation.mutate(id);
    }
  };

  const getSchoolName = (schoolId: string) => {
    const school = schools?.find(s => s.id === schoolId);
    return school?.name || 'Unknown School';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-purple-50 flex items-center justify-center">
            <GraduationCap className="h-5 w-5 text-purple-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Learners Management</h1>
            <p className="text-sm text-gray-500">Add, edit, or remove learners from the system</p>
          </div>
        </div>
        <button
          onClick={() => {
            resetForm();
            setEditingLearner(null);
            setShowCreateModal(true);
          }}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          Add Learner
        </button>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search learners..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="input pl-10 w-full"
              />
            </div>
          </div>
          <select
            value={schoolFilter}
            onChange={(e) => setSchoolFilter(e.target.value)}
            className="input w-full sm:w-48"
          >
            <option value="">All Schools</option>
            {schools?.map((school) => (
              <option key={school.id} value={school.id}>
                {school.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Learners List */}
      <div className="card">
        {isLoading ? (
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-16 bg-gray-100 rounded-lg animate-pulse" />
            ))}
          </div>
        ) : learners?.length === 0 ? (
          <div className="text-center py-8">
            <GraduationCap className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No learners found</p>
          </div>
        ) : (
          <div className="space-y-2">
            {learners?.map((learner) => (
              <div
                key={learner.id}
                className="flex items-center justify-between p-4 rounded-lg border border-gray-100 hover:border-gray-200"
              >
                <div className="flex items-center gap-4">
                  <div className="h-10 w-10 rounded-full bg-primary-100 flex items-center justify-center">
                    <span className="text-primary-700 font-medium text-sm">
                      {learner.full_name.charAt(0)}
                    </span>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{learner.full_name}</p>
                    <p className="text-sm text-gray-500">
                      {getSchoolName(learner.school_id)} • {learner.admission_no || 'No admission no.'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {learner.gender && (
                    <span className="px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                      {learner.gender}
                    </span>
                  )}
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleEdit(learner)}
                      className="p-2 text-gray-400 hover:text-primary-600 hover:bg-primary-50 rounded-lg"
                    >
                      <Edit className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(learner.id)}
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
          setEditingLearner(null);
          resetForm();
        }}
        title={editingLearner ? 'Edit Learner' : 'Add New Learner'}
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
          {!editingLearner && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                School *
              </label>
              <select
                required
                value={formData.school_id}
                onChange={(e) => setFormData({ ...formData, school_id: e.target.value })}
                className="input w-full"
              >
                <option value="">Select school</option>
                {schools?.map((school) => (
                  <option key={school.id} value={school.id}>
                    {school.name}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Admission Number
            </label>
            <input
              type="text"
              value={formData.admission_no}
              onChange={(e) => setFormData({ ...formData, admission_no: e.target.value })}
              className="input w-full"
              placeholder="Enter admission number"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Gender
            </label>
            <select
              value={formData.gender}
              onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
              className="input w-full"
            >
              <option value="">Select gender</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={() => {
                setShowCreateModal(false);
                setEditingLearner(null);
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
                : editingLearner
                ? 'Update Learner'
                : 'Create Learner'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
