// Your own films. `setup.sh` copies this to `local-films.ts` (gitignored), so films with private media stay on your machine
// and never break a teammate's Studio. Register a film here: {id, component, seconds, width?, height?}.
import type {Film} from './types';

export const LOCAL_FILMS: Film[] = [];
