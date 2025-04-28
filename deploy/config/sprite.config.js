module.exports = {
  shape: {
    id: {              // <symbol id="…">
      generator: name => `icon-${name.replace('.svg', '')}`
    }
  },
  mode: {
    symbol: {
      sprite: 'sprite.svg',   // output file name
      example: false          // no demo HTML
    }
  },
  // optional: SVGO optimisation
  svg: { xmlDeclaration: false, doctypeDeclaration: false }
};