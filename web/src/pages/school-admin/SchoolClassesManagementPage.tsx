import { useState } from 'react';
import { BookOpen, Plus, Search, Edit, Trash2 } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import { Modal } from '@/components/Modal';

interface ClassData {
  id: string;
  school_id: string;
  teacher_id: string;
  name: string;
  grade_level: string;
  learning_area_codes: string[];
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
}

interface ClassForm {
  name: string;
  grade_level: string;
  teacher_id: string;
}

interface TeacherData {
  id: string;
  full_name: string;
  email: string;
}

export function SchoolClassesManagementPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingClass, setEditingClass] = useState<ClassData | null>(null);
  const [formData, setFormData] = useState<ClassForm>({
    name: '',
    grade_level: '',
    teacher_id: '',
  });

  const { data: classes, isLoading } = useQuery<ClassData[]>({
    queryKey: ['school-admin-classes', search],
    queryFn: () => {
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      return apiFetch(`/school-admin/classes?${params.toString()}`);
    },
  });

  const { data: teachers } = useQuery<TeacherData[]>({
    queryKey: ['school-admin-teachers-list'],
    queryFn: () => apiFetch('/school-admin/teachers?limit=200'),
  });

  const createMutation = useMutation({
    mutationFn: (data: ClassForm) =>
      apiFetch('/school-admin/classes', { method: 'POST', json: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['school-admin-classes'] });
      setShowCreateModal(false);
      resetForm();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ClassForm> }) =>
      apiFetch(`/school-admin/classes/${id}`, { method: 'PATCH', json: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['school-admin-classes'] });
      setEditingClass(null);
      resetForm();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/school-admin/classes/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['school-admin-classes'] });
    },
  });

  const resetForm = () => {
    setFormData({ name: '', grade_level: '', teacher_id: '' });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingClass) {
      updateMutation.mutate({ id: editingClass.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const handleEdit = (cls: ClassData) => {
    setEditingClass(cls);
    setFormData({
      name: cls.name,
      grade_level: cls.grade_level,
      teacher_id: cls.teacher_id,
    });
    setShowCreateModal(true);
  };

  const handleDelete = (id: string) => {
    if (confirm('Are you sure you want to delete this class?')) {
      deleteMutation.mutate(id);
    }
  };

  const getTeacherName = (teacherId: string) => {
    const teacher = teachers?.find(t => t.id === teacherId);
    return teacher?.full_name || 'Unknown Teacher';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-purple-50 flex items-center justify-center">
            <BookOpen className="h-5 w-5 text-purple-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Classes Management</h1>
            <p className="text-sm text-gray-500">Add, edit, or remove classes from your school</p>
          </div>
        </div>
        <button
          onClick={() => {
            resetForm();
            setEditingClass(null);
            setShowCreateModal(true);
          }}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          Add Class
        </button>
      </div>

      {/* Search */}
      <div className="card">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search classes..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input pl-10 w-full"
          />
        </div>
      </div>

      {/* Classes List */}
      <div className="card">
        {isLoading ? (
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-16 bg-gray-100 rounded-lg animate-pulse" />
            ))}
          </div>
        ) : classes?.length === 0 ? (
          <div className="text-center py-8">
            <BookOpen className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No classes found</p>
          </div>
        ) : (
          <div className="space-y-2">
            {classes?.map((cls) => (
              <div
                key={cls.id}
                className="flex items-center justify-between p-4 rounded-lg border border-gray-100 hover:border-gray-200"
              >
                <div className="flex items-center gap-4">
                  <div className="h-10 w-10 rounded-lg bg-primary-50 flex items-center justify-center">
                    <BookOpen className="h-5 w-5 text-primary-600" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{cls.name}</p>
                    <p className="text-sm text-gray-500">
                      Grade: {cls.grade_level} • Teacher: {getTeacherName(cls.teacher_id)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handleEdit(cls)}
                    className="p-2 text-gray-400 hover:text-primary-600 hover:bg-primary-50 rounded-lg"
                  >
                    <Edit className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(cls.id)}
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
          setEditingClass(null);
          resetForm();
        }}
        title={editingClass ? 'Edit Class' : 'Add New Class'}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Class Name *
            </label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="input w-full"
              placeholder="Enter class name"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Grade Level *
            </label>
            <select
              required
              value={formData.grade_level}
              onChange={(e) => setFormData({ ...formData, grade_level: e.target.value })}
              className="input w-full"
            >
              <option value="">Select grade level...</option>
              <optgroup label="Pre-Primary">
                <option value="PP1">PP1 (Pre-Primary 1)</option>
                <option value="PP2">PP2 (Pre-Primary 2)</option>
              </optgroup>
              <optgroup label="Lower Primary (Grades 1-3)">
                <option value="Grade 1">Grade 1</option>
                <option value="Grade 2">Grade 2</option>
                <option value="Grade 3">Grade 3</option>
              </optgroup>
              <optgroup label="Upper Primary (Grades 4-6)">
                <option value="Grade 4">Grade 4</option>
                <option value="Grade 5">Grade 5</option>
                <option value="Grade 6">Grade 6</option>
              </optgroup>
              <optgroup label="Junior School (Grades 7-9)">
                <option value="Grade 7">Grade 7</option>
                <option value="Grade 8">Grade 8</option>
                <option value="Grade 9">Grade 9</option>
              </optgroup>
              <optgroup label="Senior School (Grades 10-12)">
                <option value="Grade 10">Grade 10</option>
                <option value="Grade 11">Grade 11</option>
                <option value="Grade 12">Grade 12</option>
              </optgroup>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Teacher
            </label>
            <select
              value={formData.teacher_id}
              onChange={(e) => setFormData({ ...formData, teacher_id: e.target.value })}
              className="input w-full"
            >
              <option value="">Select teacher</option>
              {teachers?.map((teacher) => (
                <option key={teacher.id} value={teacher.id}>
                  {teacher.full_name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={() => {
                setShowCreateModal(false);
                setEditingClass(null);
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
                : editingClass
                ? 'Update Class'
                : 'Create Class'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
