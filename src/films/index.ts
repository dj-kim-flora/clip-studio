// Films registered as Remotion compositions. The shipped list is empty: the generic `Clip` composition and the editorial
// template (`firstDraft` in first-draft.tsx) need no registration here. Register your own films in local-films.ts
// (copied from local-films.example.ts by setup.sh, and gitignored).
import type {Film} from './types';

export {LOCAL_FILMS} from './local-films';
export const FILMS: Film[] = [];
