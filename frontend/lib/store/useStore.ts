import { create } from 'zustand';
import { collection, doc, onSnapshot, query, orderBy, limit } from 'firebase/firestore';
import { db } from '../firebase';
import type { Job } from '../hooks/useLiveJobs'; // Temporal, luego lo movemos al store o tipos globales

export interface AppState {
  // Estado de conexión
  isOnline: boolean;
  
  // Jobs Globales (Live Feed)
  jobs: Job[];
  isLoadingJobs: boolean;
  jobsError: string | null;

  // Job Activo (Client View o HITL View)
  activeJobId: string | null;
  activeUiProjection: any | null; // El view model de Firestore
  
  // Acciones
  setOnlineStatus: (status: boolean) => void;
  setActiveJob: (jobId: string | null) => void;
  
  // Suscripciones
  subscribeToJobs: () => () => void;
  subscribeToActiveJobUI: (jobId: string) => () => void;
}

export const useStore = create<AppState>((set, get) => ({
  isOnline: true,
  jobs: [],
  isLoadingJobs: true,
  jobsError: null,
  activeJobId: null,
  activeUiProjection: null,

  setOnlineStatus: (status) => set({ isOnline: status }),
  
  setActiveJob: (jobId) => set({ activeJobId: jobId }),

  subscribeToJobs: () => {
    set({ isLoadingJobs: true, jobsError: null });
    
    const q = query(
      collection(db, 'jobs'),
      orderBy('last_update', 'desc'),
      limit(20)
    );

    const unsubscribe = onSnapshot(q, 
      (snapshot) => {
        const jobsData: Job[] = [];
        snapshot.forEach((doc) => {
          jobsData.push({ id: doc.id, ...doc.data() } as Job);
        });
        set({ jobs: jobsData, isLoadingJobs: false, isOnline: true });
      },
      (error) => {
        console.error("Error listening to jobs:", error);
        set({ jobsError: error.message, isLoadingJobs: false, isOnline: false });
      }
    );

    return unsubscribe;
  },

  subscribeToActiveJobUI: (jobId) => {
    set({ activeJobId: jobId, activeUiProjection: null });
    
    const docRef = doc(db, 'ui_projections', jobId);
    
    const unsubscribe = onSnapshot(docRef,
      (docSnap) => {
        if (docSnap.exists()) {
          set({ activeUiProjection: docSnap.data(), isOnline: true });
        } else {
          set({ activeUiProjection: null });
        }
      },
      (error) => {
        console.error("Error listening to active job UI:", error);
        set({ isOnline: false });
      }
    );

    return unsubscribe;
  }
}));
