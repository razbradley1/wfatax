import { create } from 'zustand';

const useStore = create((set, get) => ({
  // Current household context
  currentHousehold: null,
  setCurrentHousehold: (household) => set({ currentHousehold: household }),

  // Households list
  households: [],
  setHouseholds: (households) => set({ households }),

  // Loading states
  loading: false,
  setLoading: (loading) => set({ loading }),

  // Notifications
  notification: null,
  notify: (message, type = 'info') => {
    set({ notification: { message, type, id: Date.now() } });
    setTimeout(() => set({ notification: null }), 4000);
  },

  // Settings
  settings: {},
  setSettings: (settings) => set({ settings }),
}));

export default useStore;
