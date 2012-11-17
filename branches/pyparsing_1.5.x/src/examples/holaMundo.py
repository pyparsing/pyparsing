# escrito por Marco Alfonso, 2004 Noviembre

# importamos el modulo 
from pyparsing import * 
saludo= Word(alphas) + ',' + Word(alphas) + '!' 
 
# Aqui decimos que la gramatica "saludo" DEBE contener 
# una palabra compuesta de caracteres alfanumericos 
# (Word(alphas)) mas una ',' mas otra palabra alfanumerica, 
# mas '!' y esos seian nuestros tokens 
tokens = saludo.parseString("Hola, Mundo !") 
 
# Ahora parseamos una cadena, "Hola, Mundo!", 
# el metodo parseString, nos devuelve una lista con los tokens 
# encontrados, en caso de no haber errores... 
for i in range(len(tokens)):
    print "Token %d -> %s" % (i,tokens[i]) 

#imprimimos cada uno de los tokens Y listooo!!, he aquí la salida 
# Token 0—> Hola Token 1—> , Token 2—> Mundo Token 3—> ! 
 
# Por supuesto, se pueden “reutilizar” gramáticas, por ejemplo: 
numimag = Word(nums) + 'i' 
numreal = Word(nums) 
numcomplex = numreal + '+' + numimag 
print numcomplex.parseString("3+5i") 
 
# Excelente!!, bueno, los dejo, me voy a seguir tirando código…
