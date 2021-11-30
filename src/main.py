from regex_parser import RegExParser
from interpreter import Interpreter
import time
import re
from regex import RegEx
import unicodedata
import unicode


if __name__ == '__main__':
    start_time = time.time()

    test_text: str = '''Benjamin Maximillian Mehl (November 5, 1884 – September 28, 1957), usually known as B. Max Mehl, was an American dealer in coins, selling them for over half a century. The most important dealer in the U.S. through much of the first half of the 20th century, he is credited with helping to expand the appeal of coin collecting from a hobby for the wealthy to one enjoyed by many.
Mehl was born in Congress Poland, which was subjugated by the Russian Empire. His family brought him to what is now Lithuania, and then to the United States, settling in Fort Worth, Texas, where he lived for almost all of his adult life. While still a teenager, he began to sell coins, which he had previously collected. Joining the American Numismatic Association (ANA) in 1903 at age 18, he quickly became a full-time coin dealer, and by 1910 was one of the most well-known in the country.
During his half-century of coin dealing, his customer list included Franklin D. Roosevelt, Winston Churchill and Colonel E. H. R. Green. He sold coins from the collections of important numismatists (coin collectors) at auction, including Jerome Kern and King Farouk. Mehl was the first dealer to advertise in non-numismatic publications, helping to broaden the appeal of the hobby. He claimed to have spent over a million dollars on advertisements offering to buy a 1913 Liberty Head nickel for $50, though he knew there were none in circulation to be found. This got the public to search through their pocket change looking for rare coins that Mehl might buy, and greatly increased sales of Mehl's coin books, adding to his profit.
Test
Many of his great auction sales took place in the 1940s, but by the following decade, he was becoming less active, and he died in 1957; his business continued into the 1960s. Mehl was elected to the Numismatic Hall of Fame in 1974, and to the CoinFacts Dealer Hall of Fame in 2010.
Pies
Benjamin Maximillian Mehl was born on November 5, 1884,[a] in Łódź, in what was then Congress Poland within the Russian Empire. His parents, Solomon Isaac Mehl and Rachel Mehl, lived in the Jewish Quarter or ghetto of Łódź, known as Alstadt. Mehl means meal (as in ground grain, or flour), and in a time and place when last names were often descriptive of the family trade, the Mehls may have been itinerant millers.[1] Rachel Mehl's last name at birth was Goldstick.[2]
In 1885, the Mehl family, including Benjamin, moved to Vilkomu, in the province of Kovno[3] (modern day Kaunas, Lithuania). There was a growing Jewish community, and Benjamin received his initial education in its school.[1] According to a 1906 biographical sketch, he collected coins from early childhood, and was unable to recall a time when he was not interested in them.[3]
Seeking greater opportunities, in 1895 the Mehl family, including Benjamin, immigrated to the United States, arriving there in April of that year.[3][4] They initially lived in New York,[5] and settled for a time in Denton, Texas[4] before moving to Fort Worth, likely because Rachel Mehl had family there.[5] Benjamin was educated in the public schools of Fort Worth.[3] A synagogue was built in Fort Worth in 1895, which the Mehls joined; sometime around 1897, Benjamin was called to the Torah as a bar mitzvah. While attending school, Benjamin, along with his three older brothers and one older sister, was employed in the clothing store Solomon Mehl opened at 1211 Main Street in Fort Worth.[1] He left school at age 16 and became employed full-time as a clerk at the store.[2]
From the age of 10, Benjamin collected cigar bands, then stamps, then coins.[6] He dated his start as a coin dealer to 1900,[4] likely with unusual coins taken from the cash register with his father's approval as part of his pay. In June 1903, he applied to become a member of the American Numismatic Association (ANA), giving the Main Street address,[1] and using the name "B. Max Mehl"—he would never use his first name in print.[4] ANA Secretary George F. Heath noted in the ANA's journal, The Numismatist, that the thirteen applicants that month had ages ranging from 18 (Mehl's age) to 65, describing the applications as progress towards the time when every reputable coin collector or student of numismatics belonged to the ANA, adding, "the fires in the Temple of Numisma burn on and on forever."[7] In listing the collecting interests of the applicants, Heath stated that Mehl "collects only U.S. Colonial and Territorial gold and paper money". Each application was subject to no objection being lodged against the prospective member,[7] and Mehl was approved, becoming ANA member number 522 on July 1, 1903.
0XAAFF34Ω++Ω
End'''

    regex = RegEx("^[A-Z][a-z]+$")
    regex.print_graph()
    print(list(x.to_string() for x in regex.match_all(test_text)))
    print("---------------------------------------------------------------\n")

    test_text_2 = "Filipka urodziny przypadaja na 2009.03.15.人人人"
    regex = RegEx("(19|20)\\d\\d[- /.](0[1-9]|1[012])[- /.](0[1-9]|[12][0-9]|3[01])\\.人+")
    regex.print_graph()
    print(list(x.to_string() for x in regex.match_all(test_text_2)))
    print("---------------------------------------------------------------\n")

    test_text_4 = "doopa ab cd ef 1977"
    regex = RegEx("((\\w{2} ){3,4})(19|20)\\d\\d")
    regex.print_graph()
    print(list(x.to_string() for x in regex.match_all(test_text_4)))

    test_text_3 = "Filipka urodziny przypadaja na <DATE>2009.03.15</DATE>"
    regex = RegEx("<([A-Z]+)>(19|20)\\d\\d[- /.](0[1-9]|1[012])[- /.](0[1-9]|[12][0-9]|3[01])</\\1>")
    regex.print_graph()
    print(list(x.to_string() for x in regex.match_all(test_text_3)))

    """
        regex = RegEx("(.*|.*)*")
        regex.print_graph()
        print(list(x.to_string() for x in regex.match_all(test_text)))
    """
    test_text_5 = "Testing, testing today's 2021 December. Soon 2021 ends."
    regex = RegEx("(\\d{2}|\\d{4})[^0-9]+\\1")
    regex.print_graph()
    print(list(x.to_string() for x in regex.match_all(test_text_5)))
    """
        regex = RegEx("((.*)*)*")
        regex.print_graph()
        print(list(x.to_string() for x in regex.match_all(test_text)))
    """
    regex = RegEx(".*")
    regex.print_graph()
    print(list(x.to_string() for x in regex.match_all(test_text)))

    regex = RegEx("(\\d{2,4}|\\[\\d+\\])")
    regex.print_graph()
    print(list(x.to_string() for x in regex.match_all(test_text)))

    regex = RegEx("^[A-Z][a-z]+$")
    regex.print_graph()
    print(list(x.to_string() for x in regex.match_all(test_text)))

    regex = RegEx("0[xX][A-Fa-f0-9]+")  # C style hexadecimal number selection, matches e.g. 0XAAFF34
    regex.print_graph()
    print(list(x.to_string() for x in regex.match_all(test_text)))

    regex = RegEx("0[xX][A-Fa-f0-9]+\\u03A9\\x2B\\053\\p{Greek}")
    regex.print_graph()
    print(list(x.to_string() for x in regex.match_all(test_text)))

    stop_time_1 = time.time()
    print("--- %s seconds ---" % (stop_time_1 - start_time))
    # print("\N{GREEK CAPITAL LETTER OMEGA}")

    matches = re.findall("(\\d{2,4}|\\[\\d+\\])", test_text)
    print(matches)
    # stop_time_2 = time.time()
    # print("--- %s seconds ---" % (stop_time_2 - stop_time_1))

