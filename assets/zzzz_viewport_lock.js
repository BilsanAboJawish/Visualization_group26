/* Height guard for desktop Dash. Set only the CSS viewport variable;
   never scroll the document or interfere with Plotly interactions. */
(function () {
  'use strict';
  function syncViewport(){
    document.documentElement.style.setProperty('--viewport-height', window.innerHeight + 'px');
  }
  syncViewport();
  window.addEventListener('resize', syncViewport, {passive:true});
  if (window.visualViewport) window.visualViewport.addEventListener('resize', syncViewport, {passive:true});
}());
