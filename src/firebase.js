import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";

// TODO: Replace with your actual Firebase config
// To use, create a .env.local file in the root of the project with these exact keys:
// VITE_FIREBASE_API_KEY=your_key
// VITE_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
// VITE_FIREBASE_PROJECT_ID=your_project
const firebaseConfig = {
    apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "dummy_key",
    authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || "dummy_domain",
    projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "dummy_project_id",
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

export { db };
