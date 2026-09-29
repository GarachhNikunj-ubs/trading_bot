import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://zvwgolozyvjkuswtfgsm.supabase.co';
const supabasePublishableKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || 'sb_publishable_suvGvhOqqJHA19Bk0kppOA_BLyKmVP2';

export const supabase = createClient(supabaseUrl, supabasePublishableKey);

export const checkSupabaseConnection = async () => {
  try {
    const res = await fetch(`${supabaseUrl}/auth/v1/health`, {
      headers: {
        apikey: supabasePublishableKey
      }
    });
    return res.ok || res.status < 500;
  } catch (err) {
    console.error("Supabase ping error:", err);
    return false;
  }
};
