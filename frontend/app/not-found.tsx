import { interno } from '@/lib/sito';


export default function NonTrovata() {
  return (
    <div className="colonna colonna--prosa">
      <div className="giorno-vuoto">
        <p>Questa pagina non esiste.</p>
        <p>
          Il sito pubblica una pagina per giornata e una per partita.{' '}
          <a href={interno('/')}>Torna alle partite</a>.
        </p>
      </div>
    </div>
  );
}
